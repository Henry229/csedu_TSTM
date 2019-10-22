<?php
/**
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; under version 2
 * of the License (non-upgradable).
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Copyright (c) 2013-2014 (original work) Open Assessment Technologies SA (under the project TAO-PRODUCT);
 *
 * @author Jérôme Bogaerts <jerome@taotesting.com>
 * @license GPLv2
 */

namespace qtism\data\storage\xml\marshalling;

use qtism\data\QtiComponent;
use qtism\data\rules\TemplateConstraint;
use \DOMElement;
use \InvalidArgumentException;

/**
 * Marshalling/Unmarshalling implementation for TemplateConstraint.
 *
 * @author Jérôme Bogaerts <jerome@taotesting.com>
 *
 */
class TemplateConstraintMarshaller extends Marshaller
{
    /**
	 * Marshall a TemplateConstraint object into a DOMElement object.
	 *
	 * @param \qtism\data\QtiComponent $component A TemplateConstraint object.
	 * @return \DOMElement The according DOMElement object.
	 */
    protected function marshall(QtiComponent $component)
    {
        $element = static::getDOMCradle()->createElement($component->getQtiClassName());

        $marshaller = $this->getMarshallerFactory()->createMarshaller($component->getExpression());
        $element->appendChild($marshaller->marshall($component->getExpression()));

        return $element;
    }

    /**
	 * Unmarshall a DOMElement object corresponding to a QTI templateConstraint element.
	 *
	 * @param \DOMElement $element A DOMElement object.
	 * @return \qtism\data\QtiComponent A TemplateConstraint object.
	 * @throws \qtism\data\storage\xml\marshalling\UnmarshallingException
	 */
    protected function unmarshall(DOMElement $element)
    {
        $expressionElt = self::getFirstChildElement($element);

        try {
            return new TemplateConstraint($this->getMarshallerFactory()->createMarshaller($expressionElt)->unmarshall($expressionElt));
        } catch (InvalidArgumentException $e) {
            $msg = "A 'templateConstraint' element must contain an 'expression' element, '" . $expressionElt->localName . "' given.";
            throw new UnmarshallingException($msg, $element);
        }

        return new TemplateConstraint($expressions);
    }

    /**
	 * @see \qtism\data\storage\xml\marshalling\Marshaller::getExpectedQtiClassName()
	 */
    public function getExpectedQtiClassName()
    {
        return 'templateConstraint';
    }
}
